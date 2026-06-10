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
| C1 | H | DONE | doc+code | `company_filter` was a gated **phantom feature** — resolved by **deleting** it (keep practice filter, free/all-tiers) |
| C3 | M | DONE | code | Code-track benchmark submit leaks `correct` + `expected_result` mid-session (+ folded the F-06 button-label leak) |
| B1 | M | DONE | code | Free sees an **"Elite"** badge on the Pro-tier Custom drill card |
| B2 | M | DONE | code | Interview Loop summary titled **"Drill summary"** (fixed with A3) |
| B3 | M | DONE | code | History **"Time"** column shows the limit, not time used |
| B4 | M | DONE | code | Start button **enabled when `/access` fetch fails** (`accessState` null) |
| A4a | M | DONE | code | Blocked difficulty pills — added hover tooltip (notice/upgrade already shown on click) |
| A4b | M | WONTFIX | code | Locked mode cards — already gated (tooltip + lock-notice + badge + rail upsell on click) |
| A5a | M | DONE | code | Concept tags exposed on the live question (telegraphs the approach) |
| A6 | M | DONE | code | Harsh "0/X, Y% below your historical accuracy" headline tone on poor sessions |
| C4 | M | TODO | code | Discarded sessions don't count vs rate limits → create-discard cap reset |
| B7 | L | DONE | code | PySpark lobby blueprint shows a composition the backend doesn't serve |
| B5 | L | DONE | code | Elite analytics: network error indistinguishable from empty state |
| B6 | L | DONE | code | Mixed-track shows two Role selectors |
| B8 | L | DONE | code | Dead UI (`NO_MOCK_BANK_TRACKS` empty; first-run CTA hardcodes `/practice/sql`) |
| C5 | L | DONE | code | `is_follow_up` never persisted (root cause of A3) |
| C6 | L | DONE | code | `30min` legacy → generic "Invalid mode" instead of read-only message |
| C7 | L | DONE | code | Daily-cap `CURRENT_DATE` not explicitly UTC; TOCTOU on check→create |
| D2 | M | DONE | doc | `loop_summary` shape (dict vs list, missing fields); `accuracy` vs `accuracy_pct` across specs |
| D3 | M | DONE | doc | `readiness_scores`/`study_plan` live in dashboard insights, not mock analytics |
| D4 | L | DONE | doc | Discard chip window 60s (frontend) vs 120s (doc + server) |
| D5 | L | DONE | doc | Chain reclaim: spec schema says `reclaimed=TRUE`; code deletes the row |
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

### A4a — `[M]` `[DONE]` Blocked difficulty pills are clickable but silently inert
**Largely already handled; finished 2026-06-09.** Re-verified live: clicking a blocked pill already selects it and surfaces the block notice + an Upgrade button (difficulty notice + rail) with Start disabled — it is *not* silently inert. The only gap was no hover affordance, so added a `title` tooltip on blocked pills (`MockHub.js`) — e.g. "Medium, hard, and mixed benchmarks require a Pro plan." / the weekly-cap message — so the reason shows on hover without a click.

### A4b — `[M]` `[WONTFIX]` Locked mode cards clickable; switch mode "with no upsell"
**Re-verified live 2026-06-09 — already gated, no change made.** A Free user clicking the locked Custom card already sees, *before* click, a `title` tooltip + a visible lock-notice + a "Pro" badge; *after* click the rail shows a prominent upsell ("Custom drills require a Pro or Elite plan. Upgrade to practise on your own schedule. Pro unlocks this" + Upgrade button) with Start disabled. Letting the user open the locked mode and see what it offers, with a clear upgrade CTA, is a legitimate premium pattern (Linear/Notion). The original "silently switches with no upsell" framing was stale (the access-notice/upgrade machinery, reinforced by B1, already covers it). No redundant UI added.

### A5a — `[M]` `[DONE]` Concept tags exposed on the live question
**Fixed 2026-06-09.** Removed the concept-tag pills from the active mock question render (`MockSession.js`). Naming the pattern (e.g. "WINDOW FUNCTIONS") telegraphs the approach and turns recognition into recall — the opposite of what a mock should test. The post-mortem's concept breakdown still surfaces them afterward for learning. Verified live: a benchmark question whose data carries `["STRING PARSING & PATTERN MATCHING"]` renders no concept tags during the session. See `docs/decisions/DECISIONS.md` 2026-06-09.

### A5b — `[L]` `[DEFERRED]` Free benchmark time generous (60 min for 3 easy SQL) — realism tuning, optional
**Deferred 2026-06-09 (recommend leaving as-is).** Tightening benchmark time caps is a product-feel decision that risks frustrating users; "give enough time to measure ability, not induce panic" is a defensible stance and the generous cap isn't harmful. Only revisit if we deliberately want a more pressured benchmark — a per-track cap-tuning pass (`BENCHMARK_CONFIGS` / `MIXED_BENCHMARK_CONFIGS`), not a quick fix. Not blocking anything.

### A6 — `[M]` `[DONE]` Harsh "0/X, Y% below your historical accuracy" headline tone
**Fixed 2026-06-09.** Dropped the danger-red on a 0-score (now neutral `--text-strong`; green kept only for >half). Replaced the quantified shortfall: a wipeout reads "{N}/{total} solved — a tough one"; below-baseline reads "a step below your usual" (no percentage); on-par/above keep "on par with your usual" / "{delta}% above your usual". The concept breakdown + debrief below carry the "what to work on" signal, so the headline no longer piles on. `MockSession.js`; tests added. Verified live: "0/3 solved — a tough one" and "1/3 solved — a step below your usual", both neutral.

**What works (do not regress):** one-shot/timed realism, freshness scoring + chain consumption (no repeats), the Pro→Elite summary differentiation, and the Elite *debrief content* (headline + patterns + deep-linked NEXT STEP).

---

## B — UI findings

### B1 — `[M]` `[DONE]` Free sees an **"Elite"** badge on the Pro-tier Custom drill card
**Fixed 2026-06-09.** Added a `requiredTier` field to each card in `getMockModeCards` (`mockModeConfig.js`: benchmark `null`, custom `'pro'`, loop `'elite'`) and rewrote the `MockHub.js` badge to a single config-driven branch (`card.locked && card.requiredTier` → "Pro"/"Elite" with the matching class); deleted the dead `!card.locked` Pro branch. Verified live: Free sees **"Pro"** on Custom drill + "Elite" on Interview Loop; Pro sees "Elite" on Interview Loop only (custom no badge); Elite sees none. Unit tests added to `mockModeConfig.test.js`.

### B2 — `[M]` `[TODO]` Interview Loop summary titled "Drill summary"
- `MockSession.js:538` — `summaryDescriptor.isBenchmark ? 'Benchmark summary' : 'Drill summary'`; Loop has `isBenchmark:false`. Add an explicit Interview-Loop title.

### B3 — `[M]` `[DONE]` History "Time" column shows the limit, not time used
**Fixed 2026-06-09.** `time_used_s` wasn't a stored column, so `get_mock_history` (`backend/db.py`) now computes it via `EXTRACT(EPOCH FROM (ended_at - started_at))::int` (null for non-completed rows) and returns it on each row; the three history tables pass `s.time_used_s` to `formatDuration` (`MockHub.js`), which already renders "M:SS used". Test `test_history_row_includes_time_used_s`. Verified live: rows show "23:13 used", "2:49 used", etc.

### B4 — `[M]` `[DONE]` Start button enabled when `/access` fetch fails (`accessState` null)
**Fixed 2026-06-09.** The guard `(accessState && !...can_start)` short-circuited to enabled when `accessState` was null (failed fetch). Changed to `(!accessState || !...can_start)` so a null/failed access keeps Start disabled (`accessLoading` still covers the in-flight state). Extracted the access fetch into a `fetchAccess` `useCallback` and added a rail notice — "Couldn't check your access. Retry" — shown only on genuine failure (`!accessLoading && !accessState`). Test added in `MockHub.test.js` (rejected `/access` → Start disabled + Retry present). Verified live: happy path unchanged (Start enabled, no notice).

### B5 — `[L]` `[DONE]` Elite analytics: network error indistinguishable from empty state
**Fixed 2026-06-09.** Added an `analyticsError` state + extracted the fetch into a `fetchAnalytics` `useCallback`; on failure the panel now shows "Couldn't load analytics. Retry" (retry re-fetches) instead of the first-timer "Complete your first benchmark" copy. The true 0-sessions empty state is still the `total_sessions === 0` branch. `MockHub.js`; unit test added (rejected `/analytics` → error + Retry shown).

### B6 — `[L]` `[DONE]` Mixed-track shows two Role selectors
**Fixed 2026-06-09.** Hid the always-on top "Role" filter when `track === 'mixed'` (wrapped in `{!isMixedTrack && …}`), so Mixed shows only its purpose-built "Role (required)" selector. `MockHub.js`. Verified live: Mixed now shows exactly 1 role selector (was 2).

### B7 — `[L]` `[DONE]` PySpark lobby blueprint shows a composition the backend doesn't serve
**Fixed 2026-06-09.** Aligned the frontend `PYSPARK_FORMAT_TARGETS` display constant to the backend's `_pyspark_format_targets` exactly (easy/medium were wrong; medium no longer references a phantom `optimization`). `MockHub.js`. Verified: no stale `optimization` text for PySpark.

### B8 — `[L]` `[DONE]` Dead UI
**Fixed 2026-06-09.** Removed `NO_MOCK_BANK_TRACKS` (empty Set), `hasMockBank`, and the unreachable "no mock bank" note. The first-run "Warm up" CTA now routes to the selected track (`/practice/${isMixedTrack ? 'sql' : track}`, labeled "Warm up in {TRACK_LABELS[…]}") instead of hardcoded SQL. `MockHub.js`.

---

## C — Backend question-drawing / tier-correctness

**Correct (verified firsthand):** per-tier pool gating (Free no mock-only; Pro drew mock-only ids 12069/12074 + practice); chain atomicity + consumption (consumed chain 12077/12078 not re-served; a 2nd Loop drew 12079/12080) + 2-min reclaim (204); Interview Loop Elite-only; focus_concepts Elite-only; role required for Mixed; Pro 3/day independent benchmark+custom; Free 1/rolling-7-day; benchmark composition (backend) matches mock.md.

### C1 — `[H]` `[DONE]` `company_filter` was a gated **phantom feature** — resolved by deletion
- **Was:** accepted at `mock.py:115`, gated to Elite in `compute_mock_access`, but **never applied to selection** and with **no UI** — while advertised as an Elite perk on the landing page, in `pricing.md`, in the AppShell upsell, and documented in `mock.md`. So Elite was partly sold on a feature that didn't exist and that Free already had (the *practice* filter is free/all-tiers).
- **Decision (2026-06-09, user-approved):** **delete the mock company filter, keep the practice one.** A company filter is a grind-market lever at odds with the reasoning-premium positioning; the per-company pool is too thin for mock's no-repeat freshness model; and it's SQL-only. See `docs/decisions/DECISIONS.md`.
- **Shipped:** removed `company_filter` from `unlock.py` (param + gate + `MOCK_COMPANY_FILTER_TIERS`), `mock.py` (field + call site), and tests `tc133/tc134/tc149/tc150`. Purged advertising: landing Elite bullet, `pricing.md` row, AppShell upsell copy. Reconciled `mock.md` (removed the §Company Filter section + matrix row + flow step + API param), `architecture.md`, `mock-benchmark-spec.md`, `platform-north-star.md`. The **practice** SQL filter (`SidebarNav`, free, all-tiers) is unchanged. Backend mock suite 78 green.

### C3 — `[M]` `[DONE]` Code-track benchmark submit leaks `correct` + `expected_result` mid-session
**Fixed 2026-06-09.** The mid-session suppression was MCQ-only, so code-track (SQL/Python/Pandas/Stats-numerical) benchmark + interview_loop submits returned `correct`, `feedback`, and (SQL) `expected_result` — the verdict + answer key — over the wire. Replaced the MCQ-only strip in `submit_answer` (`mock.py`) with a blanket lean ack: benchmark/interview_loop return `{"submitted": True}` for **all** tracks (progress recording happens earlier via `accepted`, unaffected); custom drills keep the full result. Also folded in the coupled **F-06** leak — the code-track submit button label now shows a neutral "✓ Submitted" in benchmark/loop (was "✓ Solved"/"✗ Submitted", which revealed correctness), mirroring the MCQ button (`MockSession.js`). Regression test `test_benchmark_submit_hides_verdict_and_answer_key`. Verified live: Elite benchmark SQL submit returns only `{submitted}` — no `correct`/`expected_result`/`feedback`/`hidden_summary`. (Run, a separate endpoint, still shows the user's own output.)

### C4 — `[M]` `[TODO]` Discarded sessions don't count vs rate limits → cap reset `[mechanism confirmed]`
- `discard_mock_session` hard-deletes the row (`backend/db.py` ~1384); counters `COUNT(*)` only surviving rows. A Pro user can create→discard (within 2 min) to recover a benchmark/custom slot and re-roll without burning quota.
- **Fix approach:** either count discarded sessions toward the cap (a `discarded` tombstone) or accept-and-document. Note the legitimate use (penalty-free re-roll within 2 min) when deciding.

### C5 — `[L]` `[DONE]` `is_follow_up` never persisted (root cause of A3.2)
**Fixed 2026-06-09.** The column already existed (db.py:204, migration `20260429`) — no migration needed. `create_mock_session`'s INSERT (db.py:1253-1255) now carries `is_follow_up`, and `start_session` sets it on the loop `selected` rows (parent False, follow-ups True); benchmark/custom default False. Regression test `test_interview_loop_follow_up_flag_persisted` added. Verified live: GET now returns `is_follow_up=true` for the follow-up.

### C6 — `[L]` `[DONE]` `30min` legacy → generic "Invalid mode"
**Fixed 2026-06-09.** Added `"30min": {num_questions:2, time_limit_s:1800}` to `MODE_CONFIGS` (`mock.py`), so it joins `valid_start_modes` and hits the read-only-legacy guard. Verified live: `POST /api/mock/start {mode:"30min"}` now returns 400 "Mode '30min' is read-only legacy and cannot be started." (was generic "Invalid mode"). TC-181 tightened to assert the read-only message.

### C7 — `[L]` `[DONE — documented/accepted]` Daily-cap `CURRENT_DATE` tz + TOCTOU
**Resolved 2026-06-09 by documenting, not refactoring.** `CURRENT_DATE` is the server-tz date and the check→create has no transactional guard. Both are correct on Railway (Postgres runs UTC) and acceptable for a non-financial daily cap; refactoring prod date-math risks an off-by-a-day bug for a latent non-issue. Added docstring notes to `get_daily_benchmark_usage` (UTC assumption + accepted TOCTOU) and a pointer on `get_daily_custom_usage` (`db.py`). No SQL changed.

---

## D — Doc / SoT drift

- **D1 `[DONE]`** — Company filter advertised in SoT but absent in code: resolved with C1 (deleted everywhere; `mock.md`/`pricing.md`/landing/AppShell/specs all reconciled 2026-06-09).
- **D2 `[M]` `[DONE]`** Verified the real shape firsthand (`_compute_mock_analytics`, mock.py): `loop_summary = {sessions, per_dimension_performance: {dim_token: {attempted, correct, accuracy_pct}}}` — a **dict** keyed by token, `accuracy_pct` (percentage), and **no** `chains_completed`/`weakest_dimension`/`strongest_dimension`. Reconciled both `mock.md` and `mock-benchmark-spec.md` to this shape (resolving the cross-doc `accuracy` vs `accuracy_pct` contradiction — both now say `accuracy_pct`).
- **D3 `[M]` `[DONE]`** Confirmed `readiness_scores`/`study_plan` come from `GET /api/dashboard/insights` (insights.py, Elite), **not** `/api/mock/analytics`. Added a "Not part of this payload" note to mock.md's analytics section clarifying the matrix row groups by tier entitlement, not endpoint (trend/dimension ← analytics; debrief ← `/finish`; readiness/study-plan ← dashboard insights).
- **D4 `[L]` `[DONE]`** Confirmed the frontend has **no** countdown chip / "Discard & re-roll" button; the real UX is an early-exit modal ("Barely started — want to keep this?" → Keep going / End normally / Discard session) shown only when exiting within 60 s with no run/submit activity, while the server honours discard for 120 s. Rewrote mock.md's discard bullet to reality and noted the intentional 60 s-UI / 120 s-server margin.
- **D5 `[L]` `[DONE]`** Confirmed `discard_mock_session` **hard-deletes** the `mock_chain_consumption` row (does not set `reclaimed=TRUE`). Fixed the mock-benchmark-spec.md schema comment + added a "Reclaim is a hard delete, not a flag-flip" note; the `reclaimed` column is vestigial in the current path.
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
- **2026-06-09 — C1 + D1** — fixed on `main`. Decision: **delete the mock company filter, keep the practice one** (user-approved). Sonnet did the backend deletion; Opus did the frontend copy + docs + verification.
  - Backend: removed `company_filter` from `backend/unlock.py` (param + gate + `MOCK_COMPANY_FILTER_TIERS`) and `backend/routers/mock.py` (field + call site); removed tests `tc133/tc134/tc149/tc150`. Mock suite 78 green.
  - Frontend (advertising purge): `LandingPage.js` Elite bullet removed; `AppShell.js` upsell copy → "Unlimited mocks, Interview Loop, and per-session coaching."
  - SoT: `mock.md` (§Company Filter section + matrix row + flow step + API param removed), `pricing.md` row, `architecture.md` test desc, `mock-benchmark-spec.md` + `platform-north-star.md` filter-policy notes reconciled; `DECISIONS.md` entry appended.
  - Unchanged on purpose: the **practice** SQL company filter (`SidebarNav`, free/all-tiers) and the `companies` question tag; `frontend.md`/`CLAUDE.md` references to it are correct as-is.
- **2026-06-09 — C3 (+ F-06) + B1** — fixed on `main`. Two parallel Sonnet agents on disjoint files; Opus reviewed + verified live + committed.
  - C3: `backend/routers/mock.py` submit now returns lean `{"submitted": true}` for benchmark + interview_loop (all tracks) — no verdict/answer-key leak; custom unchanged. `MockSession.js` code-track button label neutralised to "✓ Submitted" in those modes (folds in F-06). Test `test_benchmark_submit_hides_verdict_and_answer_key`. Verified live (lean response confirmed via network).
  - B1: `mockModeConfig.js` cards gain `requiredTier`; `MockHub.js` badge is config-driven (Pro/Elite by tier, dead branch removed). Verified live: Free → "Pro" on Custom + "Elite" on Loop; Pro → "Elite" on Loop only.
  - Backend mock 79 + frontend 139 green.
- **2026-06-09 — B3 + B4** — fixed on `main`. Two parallel Sonnet agents (backend history query / frontend MockHub) on disjoint files; Opus reviewed + verified live + committed.
  - B3: `backend/db.py` `get_mock_history` computes `time_used_s` (`EXTRACT(EPOCH FROM ended_at - started_at)`); `MockHub.js` history tables pass `s.time_used_s`. Test `test_history_row_includes_time_used_s`. Verified live: "23:13 used", "2:49 used", etc.
  - B4: `MockHub.js` access fetch extracted to a `fetchAccess` `useCallback`; Start disabled when `accessState` is null (failed); "Couldn't check your access — Retry" rail notice on failure. Test in `MockHub.test.js`. Verified live (happy path unchanged).
  - Backend mock 80 + frontend 140 green.
- **2026-06-09 — D2 + D3 + D4 + D5 (docs-reconcile pass)** — docs-only, on `main`. Opus verified each claim against code firsthand, then reconciled the SoT to reality (docs serve the product). No code changed.
  - D2: `mock.md` + `mock-benchmark-spec.md` `loop_summary` → real dict shape `{sessions, per_dimension_performance:{dim:{attempted,correct,accuracy_pct}}}`; dropped unemitted `chains_completed`/`weakest`/`strongest`; resolved the `accuracy` vs `accuracy_pct` cross-doc contradiction.
  - D3: `mock.md` analytics section notes `readiness_scores`/`study_plan` come from `/api/dashboard/insights`, not `/api/mock/analytics`.
  - D4: `mock.md` discard bullet rewritten to the real early-exit modal (no countdown chip); noted 60 s-UI / 120 s-server margin.
  - D5: `mock-benchmark-spec.md` chain-reclaim corrected to "hard delete, not a flag-flip"; `reclaimed` column noted vestigial.
- **2026-06-09 — A4a + A5a (+ A4b WONTFIX, + history time-format)** — fixed on `main`. Opus did these directly (scope collapsed after live re-verification — A4a/A4b were largely pre-handled). No Sonnet needed.
  - A4a: `MockHub.js` blocked difficulty pills get a `title` tooltip (notice + upgrade already shown on click). A4b verified already-gated → WONTFIX (no redundant UI).
  - A5a: removed concept-tag pills from the active mock question render (`MockSession.js`); kept in the post-mortem. Verified live (no tags during session). DECISIONS entry appended.
  - History time-format (B3 follow-up, per user request): `formatDuration` now renders "used / limit" (e.g. "23:13 / 40:00") instead of "X used" — pacing context since caps vary by track/difficulty; mirrors the table's "Score 2/3" idiom. Verified live.
  - Frontend 145 green.
- **2026-06-09 — A6 + elite-panel toggle** — fixed on `main`. Two parallel Sonnet agents (disjoint files); Opus reviewed + verified live + committed.
  - A6: gentler post-mock headline (`MockSession.js`) — no danger-red on 0; "a tough one" (wipeout) / "a step below your usual" (below) / "{delta}% above your usual" (above). Tests added. Verified live: "0/3 solved — a tough one", "1/3 solved — a step below your usual" (neutral).
  - Elite-panel toggle (user-reported, not an audit finding): the collapse control was a bare muted arrow — added a "Hide"/"Show" text label + larger, higher-contrast arrow (`MockHub.js` + `App.css`). Verified live: shows "Hide ▴"/"Show ▾", toggles the panel.
  - Frontend 147 green.
- **2026-06-09 — B5 + B6 + B7 + B8 + C6 + C7 (low-priority cleanup batch)** — fixed on `main`. Two parallel Sonnet agents (frontend MockHub / backend); Opus reviewed + verified live + committed. A5b deferred (recommend leaving generous benchmark time as-is).
  - B5: analytics error+retry state (was indistinguishable from empty). B6: hid the duplicate top Role filter on Mixed (1 selector now). B7: aligned `PYSPARK_FORMAT_TARGETS` to the backend (no phantom `optimization`). B8: removed dead `NO_MOCK_BANK_TRACKS`/note; first-run CTA follows the selected track. (`MockHub.js`)
  - C6: `30min` added to `MODE_CONFIGS` → read-only-legacy message (`mock.py`, verified live). C7: documented the UTC + accepted-TOCTOU assumptions on the daily-usage queries (`db.py`); no SQL change.
  - Frontend 148 + backend mock 80 green.
